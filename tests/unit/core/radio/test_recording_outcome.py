"""A recording that captured nothing says so, and keeps no file.

Reported by John, 2026-08-14: pressing Record on a station that would not stay
connected gave **no confirmation that a recording had started or stopped**, and
the recordings folder was empty afterwards. The half of that Quill Radio owns is
the reporting: whatever the station does, a capture that produced nothing must be
announced as a failure with a reason, and must not leave -- or claim -- a file.

The trap these guard is specific: ffmpeg writes a container header the moment it
opens the output, so "the file exists" was never evidence that any audio arrived.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.radio import recording_outcome as outcome


def test_a_missing_file_counts_as_nothing_captured(tmp_path: Path) -> None:
    assert outcome.captured_nothing(tmp_path / "never-created.mp3")


def test_a_bare_container_header_counts_as_nothing_captured(tmp_path: Path) -> None:
    # This is the case that mattered: a file exists, and holds no audio.
    path = tmp_path / "header-only.mp3"
    path.write_bytes(b"\x00" * 512)
    assert outcome.captured_nothing(path)


def test_a_real_capture_is_kept(tmp_path: Path) -> None:
    path = tmp_path / "real.mp3"
    path.write_bytes(b"\x00" * (outcome.MIN_USEFUL_CAPTURE_BYTES + 1))
    assert not outcome.captured_nothing(path)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("[http] HTTP error 403 Forbidden", "the station refused the connection"),
        ("Server returned 404 Not Found", "that stream address is no longer there"),
        ("av_interleaved_write_frame(): No space left on device", "the disk is full"),
        ("Error opening output file: Permission denied", "that folder could not be written to"),
        ("Connection timed out", "the connection failed"),
        (
            "Invalid data found when processing input",
            "the stream was in a form it could not record",
        ),
    ],
)
def test_the_reason_is_read_from_ffmpegs_own_words(line: str, expected: str) -> None:
    assert outcome.empty_capture_reason([line]) == expected


def test_the_most_recent_line_wins() -> None:
    # ffmpeg often reports a transient error and then the one that killed it.
    tail = ["Connection timed out", "Server returned 404 Not Found"]
    assert outcome.empty_capture_reason(tail) == "that stream address is no longer there"


def test_an_unrecognised_failure_admits_it_rather_than_guessing() -> None:
    reason = outcome.empty_capture_reason(["something nobody has a pattern for"])
    assert reason == "the stream stopped before anything could be recorded"
    assert outcome.empty_capture_reason([]) == reason


def test_the_empty_file_is_removed(tmp_path: Path) -> None:
    path = tmp_path / "empty.mp3"
    path.write_bytes(b"")
    outcome.discard_empty_capture(path)
    assert not path.exists()


def test_removing_a_file_that_is_not_there_is_not_an_error(tmp_path: Path) -> None:
    # Never worth an exception on top of the failure already being reported.
    outcome.discard_empty_capture(tmp_path / "gone.mp3")


def test_a_terminal_http_code_is_fatal_and_a_transient_one_is_not() -> None:
    # 403 is deliberately transient: it is usually an expired CDN token, and
    # reconnecting is exactly the right response.
    assert outcome.is_fatal(["Server returned 404 Not Found"])
    assert outcome.is_fatal(["av_write: No space left on device"])
    assert not outcome.is_fatal(["HTTP error 403 Forbidden"])
    assert not outcome.is_fatal(["Server returned 503 Service Unavailable"])
    assert not outcome.is_fatal([])


def test_progress_lines_read_as_recovery() -> None:
    assert outcome.is_recovery("Opening 'https://example/stream' for reading")
    assert outcome.is_recovery("size=  256KiB time=00:00:29.95 bitrate=")
    assert not outcome.is_recovery("HTTP error 403 Forbidden")
