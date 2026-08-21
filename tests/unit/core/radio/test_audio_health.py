"""Audio Health answers "can this installation play and record?" when asked.

``media_preflight`` tells you once at launch when something is missing, and --
correctly -- says nothing when nothing is wrong. That leaves the opposite case
unanswered: somebody whose station will not play, or who is about to leave a
two-hour scheduled recording running, wanting to *ask*.

The trap these guard is over-reach in the other direction from
``station_confidence``: this report must never grade, score, or test. Every row
is a fact the app already holds, and a missing optional component must not be
reported as damage.
"""

from __future__ import annotations

from quill.core.radio.audio_health import (
    DEGRADED,
    OK,
    AudioHealthFacts,
    HealthRow,
    build_report,
    headline,
    media_health_of,
)


def _row(rows: list[HealthRow], label: str) -> HealthRow:
    return next(row for row in rows if row.label == label)


def _healthy(**kwargs: object) -> AudioHealthFacts:
    base: dict[str, object] = {
        "active_engine": "mpv",
        "ffmpeg_present": True,
        "mpv_present": True,
    }
    base.update(kwargs)
    return AudioHealthFacts(**base)  # type: ignore[arg-type]


def test_a_healthy_installation_still_gets_a_full_report() -> None:
    """Unlike the launch notice, this window was asked a question.

    Answering "nothing to report" with an empty list is not an answer.
    """
    rows = build_report(_healthy())
    assert len(rows) >= 8
    assert all(row.severity == OK for row in rows)
    assert headline(rows) == "Everything the radio needs to play and record is here."


def test_auto_falling_through_to_windows_media_is_named_as_such() -> None:
    # THE CASE THIS EXISTS FOR: "auto" silently selecting the lesser engine
    # because libmpv is absent. The setting still reads "automatic", which is
    # true and tells you nothing.
    rows = build_report(_healthy(active_engine="wx", mpv_present=False))
    engine = _row(rows, "Playback engine")
    assert engine.severity == DEGRADED
    assert "mpv is missing" in engine.detail
    assert "not a fault you caused" in engine.detail


def test_choosing_windows_media_deliberately_is_not_a_problem() -> None:
    rows = build_report(_healthy(active_engine="wx", engine_preference="wx"))
    assert _row(rows, "Playback engine").severity == OK
    assert "you chose it" in _row(rows, "Playback engine").detail


def test_a_missing_tool_names_what_it_costs_and_how_to_fix_it() -> None:
    rows = build_report(_healthy(ffmpeg_present=False))
    ffmpeg = _row(rows, "FFmpeg")
    assert ffmpeg.severity == DEGRADED
    assert "Help > Get FFmpeg" in ffmpeg.detail

    rows = build_report(_healthy(mpv_present=False, active_engine="wx"))
    assert "Reinstalling Quill Radio" in _row(rows, "mpv playback engine").detail


def test_a_chosen_device_the_system_no_longer_offers_is_flagged() -> None:
    rows = build_report(_healthy(output_device="USB Headset", output_device_available=False))
    device = _row(rows, "Output device")
    assert device.severity == DEGRADED
    assert "USB Headset" in device.detail
    assert "default device instead" in device.detail


def test_a_chosen_device_without_mpv_explains_why_it_is_not_used() -> None:
    # Routing needs mpv, so the device setting is real and inert at once.
    rows = build_report(_healthy(output_device="USB Headset", mpv_present=False))
    assert _row(rows, "Output device").severity == DEGRADED
    assert "routing needs mpv" in _row(rows, "Output device").detail


def test_the_default_device_is_not_something_to_report() -> None:
    assert _row(build_report(_healthy()), "Output device").detail == "the system default."


def test_a_missing_optional_component_is_never_reported_as_damage() -> None:
    # A build without the OptiLab adapter is a complete build.
    rows = build_report(_healthy(optilab_available=False))
    optilab = _row(rows, "Exact OptiLab processing")
    assert optilab.severity == OK
    assert "built-in broadcast polish is unaffected" in optilab.detail


def test_a_recording_folder_that_cannot_be_written_is_caught_before_it_matters() -> None:
    rows = build_report(_healthy(recording_folder=r"D:\Gone", recording_folder_exists=False))
    folder = _row(rows, "Recording folder")
    assert folder.severity == DEGRADED
    assert "would fail at the moment it tried to write" in folder.detail

    rows = build_report(_healthy(recording_folder=r"D:\ReadOnly", recording_folder_writable=False))
    assert _row(rows, "Recording folder").severity == DEGRADED


def test_running_recordings_are_named_so_checking_mid_capture_is_useful() -> None:
    assert "nothing is being recorded" in _row(build_report(_healthy()), "Recording now").detail
    rows = build_report(_healthy(active_recordings=1))
    assert "one recording is running" in _row(rows, "Recording now").detail
    rows = build_report(_healthy(active_recordings=3))
    assert "3 recordings are running" in _row(rows, "Recording now").detail


def test_enhancements_report_their_scope() -> None:
    rows = build_report(_healthy(enhancements_active=True, enhancements_summary="Bass +4 dB"))
    assert "for every station" in _row(rows, "Sound Enhancements").detail
    rows = build_report(
        _healthy(
            enhancements_active=True,
            enhancements_summary="Bass +4 dB",
            enhancements_per_station=True,
        )
    )
    assert "for this station only" in _row(rows, "Sound Enhancements").detail


def test_the_headline_counts_problems_rather_than_scoring_health() -> None:
    one = build_report(_healthy(ffmpeg_present=False))
    assert headline(one) == "One thing needs attention: ffmpeg."
    two = build_report(_healthy(ffmpeg_present=False, mpv_present=False, active_engine="wx"))
    line = headline(two)
    assert line.startswith("3 things need attention")  # engine, mpv and ffmpeg
    assert "playback engine" in line


def test_a_row_reads_as_one_sentence() -> None:
    row = HealthRow("Recording folder", "somewhere.")
    assert row.spoken() == "Recording folder: somewhere."


def test_the_two_tool_view_of_the_same_facts_agrees_with_it() -> None:
    health = media_health_of(_healthy(ffmpeg_present=False))
    assert health.ffmpeg is False
    assert health.mpv is True
    assert not health.healthy
