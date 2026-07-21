"""Tests for the media playback engine and player state (PRD 19.2, 19.3, 19.4)."""

from quill_social.services.media import (
    REPEAT_ALL,
    REPEAT_ONE,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_STOPPED,
    Chapter,
    MpvMediaEngine,
    NullMediaEngine,
    PlayerState,
    Track,
    player_status_text,
)


def _tracks():
    return [
        Track(uri="a.mp3", title="Alpha", kind="audio", duration_ms=10_000),
        Track(uri="b.mp3", title="Beta", kind="audio", duration_ms=6_000),
    ]


def test_null_engine_load_play_pause_stop():
    eng = NullMediaEngine()
    eng.load("a.mp3", 5000)
    assert not eng.is_playing
    eng.play()
    assert eng.is_playing
    eng.advance(2000)
    assert eng.position_ms() == 2000
    eng.pause()
    assert not eng.is_playing
    eng.advance(2000)
    assert eng.position_ms() == 2000  # no advance while paused
    eng.stop()
    assert eng.position_ms() == 0


def test_seek_clamped_to_bounds():
    eng = NullMediaEngine()
    eng.load("a.mp3", 5000)
    eng.seek_ms(-100)
    assert eng.position_ms() == 0
    eng.seek_ms(99_999)
    assert eng.position_ms() == 5000


def test_speed_scales_advance():
    eng = NullMediaEngine()
    eng.load("a.mp3", 100_000)
    eng.set_speed(2.0)
    eng.play()
    eng.advance(1000)
    assert eng.position_ms() == 2000


def test_advance_stops_at_end():
    eng = NullMediaEngine()
    eng.load("a.mp3", 3000)
    eng.play()
    eng.advance(9999)
    assert eng.position_ms() == 3000
    assert not eng.is_playing


def test_state_transitions():
    p = PlayerState()
    assert p.state == "idle"
    p.set_queue(_tracks())
    assert p.state == STATE_STOPPED
    p.play()
    assert p.state == STATE_PLAYING
    p.pause()
    assert p.state == STATE_PAUSED
    p.stop()
    assert p.state == STATE_STOPPED


def test_position_memory_across_tracks():
    p = PlayerState()
    p.set_queue(_tracks())
    p.play()
    p.tick(4000)
    assert p.engine.position_ms() == 4000
    p.next_track()
    assert p.current.uri == "b.mp3"
    # returning to the first track resumes where we left off
    p.previous_track()
    assert p.current.uri == "a.mp3"
    assert p.engine.position_ms() == 4000


def test_queue_advance_on_track_end():
    p = PlayerState()
    p.set_queue(_tracks())
    p.play()
    p.tick(10_000)  # exhaust track a (10s)
    assert p.current.uri == "b.mp3"
    assert p.state == STATE_PLAYING


def test_repeat_one_restarts_track():
    p = PlayerState()
    p.set_queue(_tracks())
    p.set_repeat(REPEAT_ONE)
    p.play()
    p.tick(10_000)
    assert p.current.uri == "a.mp3"  # did not advance
    assert p.engine.position_ms() == 0
    assert p.state == STATE_PLAYING


def test_repeat_all_wraps_queue():
    p = PlayerState()
    p.set_queue(_tracks(), start=1)  # start on last track
    p.set_repeat(REPEAT_ALL)
    p.play()
    p.tick(6000)  # exhaust track b
    assert p.current.uri == "a.mp3"


def test_stop_at_end_without_repeat():
    p = PlayerState()
    p.set_queue([Track(uri="a.mp3", duration_ms=2000)])
    p.play()
    p.tick(2000)
    assert p.state == STATE_STOPPED


def test_ab_loop_wraps_to_a():
    p = PlayerState()
    p.set_queue([Track(uri="a.mp3", title="Alpha", duration_ms=60_000)])
    p.set_ab_loop(2000, 5000)
    p.play()
    p.seek_ms(4000)
    p.tick(2000)  # would reach 6000, past B
    assert p.engine.position_ms() == 2000


def test_sleep_timer_pauses():
    p = PlayerState()
    p.set_queue(_tracks())
    p.play()
    p.set_sleep_timer(3000)
    p.tick(3000)
    assert p.state == STATE_PAUSED
    assert p.sleep_remaining_ms is None


def test_skip_forward_and_back():
    p = PlayerState()
    p.set_queue([Track(uri="a.mp3", duration_ms=100_000)])
    p.skip_ms = 5000
    p.play()
    p.seek_ms(10_000)
    p.skip_forward()
    assert p.engine.position_ms() == 15_000
    p.skip_back()
    assert p.engine.position_ms() == 10_000


def test_chapter_navigation():
    p = PlayerState()
    p.set_queue([Track(uri="a.mp3", title="Show", duration_ms=60_000)])
    p.set_chapters([Chapter(0, "Intro"), Chapter(10_000, "Topic"), Chapter(30_000, "Outro")])
    p.play()
    assert p.current_chapter().title == "Intro"
    p.next_chapter()
    assert p.engine.position_ms() == 10_000
    assert p.current_chapter().title == "Topic"
    p.previous_chapter()
    assert p.engine.position_ms() == 0


def test_status_text_speech_friendly():
    p = PlayerState()
    p.set_queue([Track(uri="a.mp3", title="Alpha", kind="audio", duration_ms=65_000)])
    p.play()
    p.tick(5000)
    text = player_status_text(p)
    assert "Playing" in text
    assert "Alpha" in text
    assert "0:05" in text
    assert "1:05" in text


def test_status_text_idle():
    p = PlayerState()
    assert "idle" in player_status_text(p).lower()


def test_mpv_engine_boundary():
    # available() must not raise regardless of whether python-mpv is installed.
    assert MpvMediaEngine.available() in (True, False)
    if not MpvMediaEngine.available():
        try:
            MpvMediaEngine()
        except RuntimeError as e:
            assert "media" in str(e).lower()
        else:
            raise AssertionError("expected RuntimeError without python-mpv")


def test_track_round_trip():
    t = Track(uri="a.mp3", title="Alpha", duration_ms=10, has_transcript=True)
    assert Track.from_dict(t.to_dict()) == t
