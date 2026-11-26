"""What Quill Radio says about an interrupted recording (FUX-05).

The offer used to show the raw ISO end time and nothing about what had been
recorded or what Resume and Skip would do; these pin the replacement words.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from quill.core.radio import resume_words as words
from quill.core.radio.recording_resume import ActiveRecordingMarker

STARTED = datetime(2026, 11, 20, 20, 0)  # a Friday, 8:00 PM


def _marker(tmp_path: Path, **changes: object) -> ActiveRecordingMarker:
    values: dict[str, object] = {
        "station_name": "WQXR",
        "stream_url": "http://example.invalid/stream",
        "temp_path": str(tmp_path / "temp" / "WQXR - show.mp3"),
        "output_path": str(tmp_path / "Recordings" / "WQXR - show.mp3"),
        "started_at": STARTED.isoformat(),
        "scheduled_end": datetime(2026, 11, 20, 21, 0).isoformat(),
        "duration_minutes": 60,
        "job_id": "abc",
    }
    values.update(changes)
    return ActiveRecordingMarker(**values)  # type: ignore[arg-type]


def _part(path: Path, minutes: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"audio")
    stamp = STARTED.timestamp() + minutes * 60
    os.utime(path, (stamp, stamp))
    return path


def test_offer_names_the_work_and_each_choice(tmp_path):
    marker = _marker(tmp_path)
    part = _part(tmp_path / "Recordings" / "WQXR - show (2).mp3", 23)
    seconds = words.recorded_seconds(marker, part)
    where = words.kept_where(part, str(tmp_path / "Recordings"))
    text = words.offer_sentence(marker, left=37, seconds=seconds, where=where)
    assert text.startswith(
        "Your recording of WQXR, started Friday 8:00 PM and due to end at 9:00 PM, "
        "stopped unexpectedly."
    )
    assert "What it recorded, 23 minutes, is kept in your recordings folder." in text
    assert "Resume records the remaining 37 minutes as a separate file." in text
    assert "Skip records nothing more." in text
    assert "nothing already recorded is deleted" in text
    assert "2026-11-20" not in text and "T21" not in text


def test_partial_file_follows_the_move_home_and_its_free_name(tmp_path):
    marker = _marker(tmp_path)
    moved = _part(tmp_path / "Recordings" / "WQXR - show (2).mp3", 5)
    other = _part(tmp_path / "Recordings" / "KUSC - other.mp3", 5)
    assert words.partial_file(marker, [other, moved]) == moved
    assert words.unclaimed([other, moved], [marker]) == [other]


def test_partial_file_left_in_temp_is_found_and_said_so(tmp_path):
    marker = _marker(tmp_path)
    left = _part(Path(marker.temp_path), 10)
    assert words.partial_file(marker, []) == left
    assert (
        words.kept_where(left, str(tmp_path / "Recordings"), str(tmp_path / "temp"))
        == "in the temporary recording folder"
    )


def test_nothing_found_is_said_rather_than_claimed(tmp_path):
    marker = _marker(tmp_path)
    assert words.partial_file(marker, []) is None
    text = words.cut_short_sentence(marker, seconds=None, where="")
    assert text == (
        "Your recording of WQXR, started Friday 8:00 PM, stopped unexpectedly before it "
        "was due to end at 9:00 PM. Nothing it recorded before then was found."
    )


def test_recorded_time_never_exceeds_the_booking(tmp_path):
    marker = _marker(tmp_path)
    part = _part(tmp_path / "Recordings" / "WQXR - show.mp3", 500)
    assert words.recorded_seconds(marker, part) == 3600


def test_batch_line_and_failure_and_moved_sentences(tmp_path):
    marker = _marker(tmp_path)
    assert (
        words.batch_line(marker, left=12, seconds=600)
        == "WQXR, started Friday 8:00 PM: 10 minutes recorded, 12 minutes left"
    )
    failed = words.resume_failed_sentence(marker)
    assert failed == "The recording of WQXR could not be resumed. What it recorded before is kept."
    moved = words.moved_sentence(
        [Path("C:/R/KUSC - Friday.mp3"), Path("C:/R/Jazz.mka")], "your recordings folder"
    )
    assert moved == (
        "Moved 2 recordings left in the temporary folder after an unexpected close to "
        "your recordings folder: KUSC - Friday; Jazz."
    )
    assert words.moved_sentence([], "anywhere") == ""
