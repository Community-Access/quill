"""Resuming a recording where you stopped -- the controller-facing half."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.radio.models import RadioStation
from quill.core.radio.resume import ResumeStore
from quill.ui.radio import resume_playback as rp


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    rp.set_store_for_tests(ResumeStore(tmp_path))
    yield
    rp.set_store_for_tests(None)


def _host(station, *, seekable=True, position=0, duration=0):
    return SimpleNamespace(
        _state=SimpleNamespace(station=station),
        is_seekable=lambda: seekable,
        position_ms=lambda: position,
        duration_ms=lambda: duration,
    )


def _recording(url="https://a.example/ch1.mp3"):
    return RadioStation(name="Chapter 1", stream_url=url, is_recording=True)


def _live(url="https://ice.example/stream"):
    return RadioStation(name="Jazz FM", stream_url=url)


def test_a_recording_remembers_and_resumes() -> None:
    station = _recording()
    rp.remember(_host(station, position=600_000, duration=3_600_000))
    assert rp.saved_position_ms(station) == 600_000


def test_a_live_station_is_never_remembered() -> None:
    # You tune in and you are where everyone else is; there is no place to keep.
    station = _live()
    rp.remember(_host(station, position=600_000, duration=0))
    assert rp.saved_position_ms(station) == 0


def test_a_recording_that_is_not_yet_seekable_is_not_remembered() -> None:
    station = _recording()
    rp.remember(_host(station, seekable=False, position=600_000, duration=3_600_000))
    assert rp.saved_position_ms(station) == 0


def test_forget_starts_from_the_beginning_next_time() -> None:
    station = _recording()
    host = _host(station, position=600_000, duration=3_600_000)
    rp.remember(host)
    rp.forget(host)
    assert rp.saved_position_ms(station) == 0


def test_nothing_raises_when_the_host_is_half_built() -> None:
    # The transport tests build a controller with no state at all.
    rp.remember(SimpleNamespace())
    rp.forget(SimpleNamespace())
    assert rp.saved_position_ms(None) == 0


def test_is_recording_reads_the_flag_not_the_source() -> None:
    assert rp.is_recording(_recording())
    assert not rp.is_recording(_live())
    assert not rp.is_recording(None)


# --- the announcement, which is configurable --------------------------------


def test_spoken_says_where_it_is_resuming_from() -> None:
    assert rp.announcement(728_000) == "Resuming at 12 minutes 8 seconds."


def test_brief_says_only_that_it_is_resuming() -> None:
    assert rp.announcement(728_000, verbosity="brief") == "Resuming."


def test_silent_says_nothing() -> None:
    assert rp.announcement(728_000, verbosity="silent") == ""


def test_nothing_to_resume_says_nothing_whatever_the_setting() -> None:
    # So a caller can announce unconditionally and never emit an empty utterance.
    for verbosity, _label in rp.VERBOSITIES:
        assert rp.announcement(0, verbosity=verbosity) == ""


def test_an_unknown_setting_falls_back_to_spoken() -> None:
    # A mis-set preference must not silently remove information.
    assert rp.announcement(728_000, verbosity="nonsense").startswith("Resuming at")


def test_the_setting_exists_with_the_documented_default() -> None:
    from quill.core.settings import Settings

    assert Settings().radio_resume_announcement == "spoken"
    assert {v for v, _l in rp.VERBOSITIES} == {"spoken", "brief", "silent"}
