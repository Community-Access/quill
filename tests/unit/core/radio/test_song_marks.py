"""Song marks in the time-shift buffer (an idea from BlindRadio by serrebidev, MIT)."""

from __future__ import annotations

import pytest

from quill.core.radio import song_marks as sm
from quill.core.radio.song_marks import Song, SongMarks, Which


def _marks(*pairs: tuple[str, float], station: str = "") -> SongMarks:
    marks = SongMarks(station)
    for title, position in pairs:
        assert marks.mark(title, position)
    return marks


# -- marking --------------------------------------------------------------------


def test_titles_mark_once_and_blanks_mark_nothing() -> None:
    marks = SongMarks()
    assert marks.mark("Artist - One", 100.0)
    assert not marks.mark("Artist - One", 130.0)  # the same song, heard again
    assert not marks.mark("", 140.0)
    assert not marks.mark("   ", 150.0)
    assert marks.mark("Artist - Two", 300.0)
    assert [m.title for m in marks.marks] == ["Artist - One", "Artist - Two"]


@pytest.mark.parametrize("noise", ["Live", "Advertisement", "Commercial", "KXYZ FM"])
def test_noise_titles_mark_nothing(noise: str) -> None:
    marks = SongMarks("KXYZ FM")
    marks.mark("Artist - One", 100.0)
    assert not marks.mark(noise, 200.0)
    assert marks.title_at(250.0) == "Artist - One"


def test_station_name_comes_from_reset() -> None:
    marks = SongMarks()
    marks.mark("A - One", 10.0)
    marks.reset("Jazz 24")
    assert len(marks) == 0
    assert not marks.mark("Jazz 24", 20.0)
    assert marks.station_name == "Jazz 24"


def test_a_first_title_soon_after_tuning_in_names_the_audio_before_it() -> None:
    marks = SongMarks()
    marks.mark("A - One", 8.0, buffer_start=0.0)
    assert marks.marks[0].position == 0.0


def test_a_late_first_title_is_marked_where_it_arrived() -> None:
    marks = SongMarks()
    marks.mark("A - One", 40.0, buffer_start=0.0)
    assert marks.marks[0].position == 40.0


def test_a_second_sighting_moves_the_mark_earlier_never_later() -> None:
    """The live-edge reader sees a title up to a poll late; mpv's timed title is exact."""
    marks = SongMarks()
    marks.mark("A - One", 0.0)
    assert marks.mark("B - Two", 230.0)  # out-of-band, at the live edge
    assert marks.mark("B - Two", 205.0)  # mpv, when playback reached it
    assert [m.position for m in marks.marks] == [0.0, 205.0]
    assert not marks.mark("B - Two", 240.0)
    assert [m.position for m in marks.marks] == [0.0, 205.0]


def test_an_earlier_sighting_never_crosses_the_song_before() -> None:
    marks = _marks(("A - One", 100.0), ("B - Two", 130.0))
    assert not marks.mark("B - Two", 90.0)
    assert marks.marks[1].position == 130.0


def test_replaying_a_marked_song_after_a_rewind_marks_nothing() -> None:
    marks = _marks(("A - One", 0.0), ("B - Two", 200.0), ("C - Three", 400.0))
    assert not marks.mark("B - Two", 320.0)  # rewound into B; mpv reports it again
    assert len(marks) == 3


def test_marks_insert_in_order_even_when_they_arrive_out_of_order() -> None:
    marks = _marks(("C - Three", 400.0), ("A - One", 0.0), ("B - Two", 200.0))
    assert [m.title for m in marks.marks] == ["A - One", "B - Two", "C - Three"]


def test_forget_before_keeps_only_the_mark_the_oldest_audio_falls_under() -> None:
    marks = _marks(("A - One", 0.0), ("B - Two", 100.0), ("C - Three", 200.0))
    marks.forget_before(150.0)
    assert [m.title for m in marks.marks] == ["B - Two", "C - Three"]
    marks.forget_before(500.0)
    assert [m.title for m in marks.marks] == ["C - Three"]


def test_title_at_names_the_song_of_the_moment() -> None:
    marks = _marks(("A - One", 10.0), ("B - Two", 100.0))
    assert marks.title_at(5.0) == ""
    assert marks.title_at(10.0) == "A - One"
    assert marks.title_at(99.9) == "A - One"
    assert marks.title_at(100.0) == "B - Two"


# -- songs ------------------------------------------------------------------------


def test_the_oldest_song_starts_where_the_buffer_does_and_the_newest_runs_to_live() -> None:
    marks = _marks(("A - One", 0.0), ("B - Two", 100.0), ("C - Three", 200.0))
    assert marks.songs(50.0, 260.0) == [
        Song("A - One", 50.0, 100.0),
        Song("B - Two", 100.0, 200.0),
        Song("C - Three", 200.0, 260.0),
    ]


def test_a_song_with_no_audio_left_is_not_a_song() -> None:
    marks = _marks(("A - One", 0.0), ("B - Two", 100.0))
    assert [s.title for s in marks.songs(100.0, 150.0)] == ["B - Two"]
    assert marks.songs(0.0, 0.0) == []


# -- pick and jump ------------------------------------------------------------------

_SONGS = [Song("A", 0.0, 100.0), Song("B", 100.0, 200.0), Song("C", 200.0, 260.0)]


def test_pick_is_relative_to_the_playhead() -> None:
    assert sm.pick(_SONGS, 150.0, Which.CURRENT) == [_SONGS[1]]
    assert sm.pick(_SONGS, 150.0, Which.PREVIOUS) == [_SONGS[0]]
    assert sm.pick(_SONGS, 150.0, Which.NEXT) == [_SONGS[2]]
    assert sm.pick(_SONGS, 150.0, Which.ALL) == _SONGS


def test_pick_at_the_edges() -> None:
    assert sm.pick(_SONGS, 50.0, Which.PREVIOUS) == []
    assert sm.pick(_SONGS, 250.0, Which.NEXT) == []
    late = [Song("A", 10.0, 20.0)]
    assert sm.pick(late, 5.0, Which.CURRENT) == []
    assert sm.pick(late, 5.0, Which.NEXT) == late
    assert sm.pick([], 5.0, Which.ALL) == []


def test_previous_restarts_a_song_you_are_well_into() -> None:
    assert sm.jump(_SONGS, 150.0, forward=False, behind_live=True).song == _SONGS[1]


def test_previous_just_after_a_start_goes_to_the_song_before() -> None:
    assert sm.jump(_SONGS, 101.0, forward=False, behind_live=True).song == _SONGS[0]


def test_previous_at_the_oldest_song_restarts_it_then_goes_nowhere() -> None:
    assert sm.jump(_SONGS, 50.0, forward=False, behind_live=True).song == _SONGS[0]
    assert sm.jump(_SONGS, 1.0, forward=False, behind_live=True).nowhere


def test_next_steps_on_and_past_the_last_returns_to_live() -> None:
    assert sm.jump(_SONGS, 150.0, forward=True, behind_live=True).song == _SONGS[2]
    assert sm.jump(_SONGS, 210.0, forward=True, behind_live=True).live


def test_next_while_live_goes_nowhere() -> None:
    assert sm.jump(_SONGS, 258.0, forward=True, behind_live=False).nowhere


# -- small helpers ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("seconds", "spoken"),
    [
        (0, "0 seconds"),
        (1, "1 second"),
        (59.6, "1 minute"),
        (65, "1 minute 5 seconds"),
        (3600, "1 hour"),
        (3720, "1 hour 2 minutes"),
    ],
)
def test_describe_offset(seconds: float, spoken: str) -> None:
    assert sm.describe_offset(seconds) == spoken


@pytest.mark.parametrize(
    ("codec", "extension"),
    [("mp3", ".mp3"), ("AAC", ".aac"), ("opus", ".opus"), ("vorbis", ".ogg"), ("", ".mka")],
)
def test_songs_keep_the_station_format(codec: str, extension: str) -> None:
    assert sm.extension_for_codec(codec) == extension
