"""11.7: speed and Skip Silence for the things Radio plays that are not live.

The engine could always do both -- ``audio_enhance``'s Smart Speed clause
carried the comment "podcasts only; radio callers never pass
``smart_speed_enabled=True``" -- and Quill Radio never passed it, and never
remembered a speed for anything that was not a podcast episode.
"""

from __future__ import annotations

from quill.core.radio import bounded_prefs
from quill.core.radio.history import RadioHistory
from quill.core.radio.models import RadioStation


def _station(**kwargs: object) -> RadioStation:
    fields: dict = {"name": "Something", "stream_url": "https://example.com/x.mp3"}
    fields.update(kwargs)
    return RadioStation(**fields)  # type: ignore[arg-type]


def test_a_local_file_is_a_recording_however_it_was_reached() -> None:
    """A recording opened from the Recordings window carries no source at all."""
    assert bounded_prefs.kind_for(_station(stream_url=r"C:\\Recordings\\WQXR.mp3")) == (
        bounded_prefs.KIND_RECORDING
    )


def test_a_youtube_row_is_its_own_kind() -> None:
    assert bounded_prefs.kind_for(_station(source="YouTube")) == bounded_prefs.KIND_YOUTUBE


def test_an_ordinary_http_station_is_live() -> None:
    assert bounded_prefs.kind_for(_station(source="Radio Browser")) == bounded_prefs.KIND_LIVE


def test_nothing_playing_is_not_a_kind_that_remembers_anything() -> None:
    assert bounded_prefs.kind_for(None) == bounded_prefs.KIND_OTHER
    assert bounded_prefs.remembers_speed(bounded_prefs.KIND_OTHER) is False


def test_only_recordings_and_youtube_remember_a_speed_here() -> None:
    """Podcasts are remembered per show elsewhere; live radio has no speed."""
    assert bounded_prefs.remembers_speed(bounded_prefs.KIND_RECORDING) is True
    assert bounded_prefs.remembers_speed(bounded_prefs.KIND_YOUTUBE) is True
    assert bounded_prefs.remembers_speed(bounded_prefs.KIND_PODCAST) is False
    assert bounded_prefs.remembers_speed(bounded_prefs.KIND_LIVE) is False


def test_a_speed_is_remembered_per_kind_and_read_back() -> None:
    history = RadioHistory()
    assert bounded_prefs.speed_for_kind(history, bounded_prefs.KIND_RECORDING) == 1.0
    assert bounded_prefs.set_speed_for_kind(history, bounded_prefs.KIND_RECORDING, 1.5) is True
    assert history.recording_speed == 1.5
    assert bounded_prefs.speed_for_kind(history, bounded_prefs.KIND_RECORDING) == 1.5
    assert bounded_prefs.speed_for_kind(history, bounded_prefs.KIND_YOUTUBE) == 1.0


def test_a_kind_that_is_not_remembered_writes_nothing() -> None:
    history = RadioHistory()
    assert bounded_prefs.set_speed_for_kind(history, bounded_prefs.KIND_LIVE, 2.0) is False
    assert history.recording_speed == 1.0 and history.youtube_speed == 1.0


def test_a_stored_speed_outside_mpvs_range_is_clamped_on_the_way_in_and_out() -> None:
    history = RadioHistory()
    bounded_prefs.set_speed_for_kind(history, bounded_prefs.KIND_YOUTUBE, 99.0)
    assert history.youtube_speed == bounded_prefs.SPEED_MAX
    history.recording_speed = 0.01
    assert bounded_prefs.speed_for_kind(history, bounded_prefs.KIND_RECORDING) == (
        bounded_prefs.SPEED_MIN
    )


def test_a_nonsense_stored_speed_reads_as_normal() -> None:
    history = RadioHistory()
    history.recording_speed = "fast"  # type: ignore[assignment]
    assert bounded_prefs.speed_for_kind(history, bounded_prefs.KIND_RECORDING) == 1.0


def test_skip_silence_on_live_radio_says_it_will_do_nothing() -> None:
    """Saying only "Skip Silence on" would be true and impossible to hear."""
    spoken = bounded_prefs.describe_skip_silence(True, bounded_prefs.KIND_LIVE)
    assert "no effect on live radio" in spoken
    assert "recordings" in spoken


def test_skip_silence_on_something_bounded_says_what_changes() -> None:
    assert bounded_prefs.describe_skip_silence(True, bounded_prefs.KIND_RECORDING) == (
        "Skip Silence on. Long pauses are shortened as this plays."
    )
    assert bounded_prefs.describe_skip_silence(False, bounded_prefs.KIND_RECORDING) == (
        "Skip Silence off. Pauses play at their full length again."
    )


def test_the_speed_tail_names_the_kind_it_was_remembered_for() -> None:
    assert bounded_prefs.speed_sentence(1.5, bounded_prefs.KIND_RECORDING) == (
        " Remembered for recordings."
    )
    assert bounded_prefs.speed_sentence(1.0, bounded_prefs.KIND_YOUTUBE) == (
        " Youtube rows will play at normal speed."
    )
    assert bounded_prefs.speed_sentence(1.5, bounded_prefs.KIND_LIVE) == ""


def test_the_three_fields_round_trip_through_the_history_file(tmp_path) -> None:
    from quill.core.radio.history import load_history, save_history

    history = RadioHistory()
    history.skip_silence = True
    history.recording_speed = 1.75
    history.youtube_speed = 2.0
    save_history(tmp_path, history)
    back = load_history(tmp_path)
    assert back.skip_silence is True
    assert back.recording_speed == 1.75
    assert back.youtube_speed == 2.0
