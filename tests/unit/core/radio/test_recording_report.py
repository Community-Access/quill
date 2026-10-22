"""How a radio recording ended, in one sentence (recording_report).

The case behind it: a 190-minute scheduled show that ended with no recording
the listener could find. These pin the sentence that now tells them how long
the recording is, where it is, and -- when it ended before its time -- why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from quill.core.radio import recording_outcome
from quill.core.radio.recording_report import (
    ENDED_EARLY,
    FINISHED,
    STOPPED,
    RecordingReport,
    build_report,
    describe,
    format_length,
)

START = datetime(2026, 10, 16, 16, 58)


@dataclass
class _Settings:
    reconnect_enabled: bool = True


@dataclass
class _Job:
    job_id: str = "j1"
    station_name: str = "WNYC"
    started_at: datetime = START
    scheduled_end: datetime = START + timedelta(minutes=190)
    duration_requested: bool = True
    destination: Path = Path("rec/show.mp3")
    final_destination: Path = Path("rec/show.mp3")
    reconnect_attempt: int = 0
    user_stopped: bool = False
    settings: _Settings = field(default_factory=_Settings)


def _report(
    job: _Job,
    *,
    at: datetime,
    dropped: bool = False,
    fatal: bool = False,
    tail: list[str] | None = None,
    path: Path | None = None,
) -> RecordingReport:
    return build_report(
        job,
        path if path is not None else job.final_destination,
        dropped=dropped,
        fatal=fatal,
        stderr_tail=tail or [],
        now=at,
    )


def test_format_length_reads_naturally() -> None:
    assert format_length(0) == "under a minute"
    assert format_length(59) == "under a minute"
    assert format_length(60) == "1 minute"
    assert format_length(44 * 60) == "44 minutes"
    assert format_length(3600) == "1 hour"
    assert format_length(184 * 60 + 30) == "3 hours 4 minutes"


def test_stopping_early_is_a_saved_recording_with_its_length_and_folder() -> None:
    # Rick's case: Stop All at 8:02 on a show scheduled to 8:08.
    job = _Job(user_stopped=True)
    report = _report(job, at=START + timedelta(minutes=184), dropped=True)
    assert report.how == STOPPED
    assert describe(report) == (
        "Recording saved: WNYC, started Friday 4:58 PM, 3 hours 4 minutes, in rec."
    )


def test_running_to_its_end_is_finished() -> None:
    report = _report(_Job(), at=START + timedelta(minutes=190))
    assert report.how == FINISHED
    assert describe(report).startswith("Recording saved: WNYC, started Friday 4:58 PM, 3 hours")


def test_a_drop_at_the_very_end_is_the_show_ending_not_a_failure() -> None:
    report = _report(_Job(), at=START + timedelta(minutes=189, seconds=30), dropped=True)
    assert report.how == FINISHED


def test_giving_up_after_reconnects_says_how_early_and_why() -> None:
    job = _Job(reconnect_attempt=5)
    report = _report(job, at=START + timedelta(minutes=44), dropped=True)
    assert report.how == ENDED_EARLY
    assert report.planned_seconds == 190 * 60
    # How much was saved leads; the cause is its own last sentence.
    assert describe(report) == (
        "WNYC recording ended early. Saved 44 of 190 minutes, in rec. Reason: the "
        "station stopped responding and did not come back after 5 reconnect attempts."
    )


def test_a_fatal_drop_names_the_cause_from_ffmpeg() -> None:
    report = _report(
        _Job(),
        at=START + timedelta(minutes=30),
        dropped=True,
        fatal=True,
        tail=["Server returned 404 Not Found"],
    )
    assert report.reason == "that stream address is no longer there"


def test_reconnect_off_says_so_and_where_to_change_it() -> None:
    job = _Job(settings=_Settings(reconnect_enabled=False))
    report = _report(job, at=START + timedelta(minutes=30), dropped=True)
    assert "reconnecting is turned off in Recording Settings" in describe(report)


def test_an_open_ended_capture_that_drops_stopped_on_its_own() -> None:
    # No length was chosen, so there is no "early" to measure against.
    job = _Job(duration_requested=False, scheduled_end=START + timedelta(hours=8))
    report = _report(job, at=START + timedelta(minutes=20), dropped=True)
    assert report.planned_seconds == 0
    assert describe(report).startswith("WNYC recording stopped on its own. Saved 20 minutes, in")


def test_a_file_left_in_the_temp_folder_says_so() -> None:
    job = _Job(destination=Path("tmp/show.mp3"), final_destination=Path("rec/show.mp3"))
    report = _report(job, at=START + timedelta(minutes=190), path=Path("tmp/show.mp3"))
    assert report.left_in_temp
    assert describe(report).endswith(
        "3 hours 10 minutes, but not in your recordings folder: it is still in the "
        "temporary recording folder."
    )


def test_reason_from_stderr_is_empty_when_nothing_matches() -> None:
    assert recording_outcome.reason_from_stderr(["frame=  10 size= 1kB"]) == ""
    assert (
        recording_outcome.empty_capture_reason([])
        == "the stream stopped before anything could be recorded"
    )
