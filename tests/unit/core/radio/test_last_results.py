"""Reopen Last Results: round trip, damage is ignored, public addresses only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.radio import last_results as lr
from quill.core.radio.page_links import PageStreamCandidate


def _results(n: int = 3) -> lr.LastResults:
    cands = [
        PageStreamCandidate(
            url=f"https://example.com/s{i}.mp3",
            reason="audio tag",
            label=f"Stream {i}",
            check="live",
            codec="MP3",
            bitrate_kbps=128,
            stream_name=f"Name {i}",
            listeners=i,
        )
        for i in range(n)
    ]
    return lr.LastResults(
        page_url="https://example.com/radio",
        candidates=cands,
        page_title="Example",
        order="name",
        format="MP3",
        live_only=True,
        current="https://example.com/s1.mp3",
        saved_at=1000.0,
    )


def test_round_trip_keeps_rows_filter_order_and_current_row(tmp_path: Path) -> None:
    lr.save(tmp_path, _results())
    back = lr.load(tmp_path)
    assert back is not None
    assert [c.url for c in back.candidates] == [c.url for c in _results().candidates]
    assert (back.order, back.format, back.live_only) == ("name", "MP3", True)
    assert back.current == "https://example.com/s1.mp3"
    assert back.candidates[2].listeners == 2 and back.candidates[0].stream_name == "Name 0"


def test_missing_file_is_none(tmp_path: Path) -> None:
    assert lr.load(tmp_path) is None


@pytest.mark.parametrize(
    "text", ["", "not json", "[]", "null", '{"version": 99}', '{"version": 1, "candidates": 5}']
)
def test_damaged_file_is_ignored_quietly(tmp_path: Path, text: str) -> None:
    (tmp_path / lr.FILE_NAME).write_text(text, encoding="utf-8")
    assert lr.load(tmp_path) is None


def test_bad_rows_are_dropped_and_empty_means_none() -> None:
    raw = lr.to_json(_results(2))
    raw["candidates"] = [
        "junk",
        {"url": "ftp://x/y"},
        {"url": "http://localhost/a"},
        {"url": "http://192.168.1.2/a"},
        {"url": "https://ok.example.com/a", "bitrate_kbps": "fast", "listeners": -4},
    ]
    back = lr.from_json(raw)
    assert back is not None and [c.url for c in back.candidates] == ["https://ok.example.com/a"]
    assert back.candidates[0].bitrate_kbps == 0 and back.candidates[0].listeners is None
    raw["candidates"] = ["junk"]
    assert lr.from_json(raw) is None


def test_unknown_order_and_format_fall_back() -> None:
    raw = lr.to_json(_results())
    raw["order"], raw["format"] = "sideways", "WMA"
    back = lr.from_json(raw)
    assert back is not None and (back.order, back.format) == ("scan", "")


def test_rows_are_capped() -> None:
    results = _results(lr.MAX_STREAMS + 20)
    assert len(lr.to_json(results)["candidates"]) == lr.MAX_STREAMS


def test_clear(tmp_path: Path) -> None:
    lr.save(tmp_path, _results())
    assert lr.clear(tmp_path) is True and lr.clear(tmp_path) is False
    assert lr.load(tmp_path) is None


def test_unwritable_directory_is_ignored(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    lr.save(blocker, _results())  # a file where the folder should be: no exception


def test_sentences_are_plain() -> None:
    r = _results(1)
    assert lr.offer_sentence(r) == (
        "Your last results are saved: 1 stream from example.com. "
        "Choose Reopen Last Results to see them."
    )
    assert lr.reopened_sentence(r, now=1030.0) == (
        "Reopened 1 stream from example.com, found a moment ago. Nothing was scanned or played."
    )
    assert "3 hours ago" in lr.reopened_sentence(r, now=1000.0 + 3 * 3600)
    assert json.dumps(lr.to_json(r))  # serialisable


def test_a_files_size_and_date_survive_reopening(tmp_path: Path) -> None:
    results = _results(1)
    results.candidates[0].size_bytes = 3_400_000
    results.candidates[0].modified = "2020-05-01 14:30"
    lr.save(tmp_path, results)
    back = lr.load(tmp_path)
    assert back is not None
    assert (back.candidates[0].size_bytes, back.candidates[0].modified) == (
        3_400_000,
        "2020-05-01 14:30",
    )
    raw = lr.to_json(results)
    raw["candidates"][0]["size_bytes"] = "huge"
    assert lr.from_json(raw).candidates[0].size_bytes == 0  # type: ignore[union-attr]
