"""Tests for the recently-played radio history store."""

from __future__ import annotations

from pathlib import Path

from quill.core.radio.history import RadioHistory, load_history, save_history
from quill.core.radio.models import RadioStation


def _station(name: str, uuid: str = "") -> RadioStation:
    return RadioStation(name=name, stream_url=f"https://{name}.example.com", station_uuid=uuid)


def test_record_moves_repeat_plays_to_the_front_without_duplicates() -> None:
    history = RadioHistory()
    a, b = _station("a", "u-a"), _station("b", "u-b")
    history.record(a)
    history.record(b)
    history.record(a)
    assert [s.name for s in history.stations] == ["a", "b"]
    assert history.last_station is not None and history.last_station.name == "a"


def test_history_is_capped() -> None:
    history = RadioHistory()
    for i in range(30):
        history.record(_station(f"s{i}", f"u{i}"))
    assert len(history.stations) == 15
    assert history.stations[0].name == "s29"


def test_round_trip_and_missing_file(tmp_path: Path) -> None:
    assert load_history(tmp_path).stations == []
    history = RadioHistory(resume_on_launch=True)
    history.record(_station("keep", "u-k"))
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert loaded.resume_on_launch is True
    assert loaded.last_station is not None and loaded.last_station.name == "keep"


def test_corrupt_file_reads_empty(tmp_path: Path) -> None:
    (tmp_path / "radio_history.json").write_text("nope", encoding="utf-8")
    history = load_history(tmp_path)
    assert history.stations == [] and history.resume_on_launch is False
