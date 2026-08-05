"""Unit tests for ``quill.core.media.timecode``."""

from __future__ import annotations

import pytest

from quill.core.media import (
    InvalidTimecodeError,
    format_spoken,
    format_timecode,
    parse_timecode,
)


@pytest.mark.parametrize(
    ("text", "ms"),
    [
        ("1:23:45", 5_025_000),
        ("83:45", 5_025_000),  # mm:ss with minutes over 59 is allowed in the first segment
        ("0:30", 30_000),
        ("5025", 5_025_000),  # whole seconds
        ("1h23m45s", 5_025_000),
        ("2m", 120_000),
        ("45s", 45_000),
    ],
)
@pytest.mark.smoke
def test_parse_valid(text: str, ms: int) -> None:
    assert parse_timecode(text) == ms


@pytest.mark.parametrize("bad", ["", "   ", "abc", "1:2:3:4", "1:99", "-5", "1:2:xx"])
def test_parse_invalid(bad: str) -> None:
    with pytest.raises(InvalidTimecodeError):
        parse_timecode(bad)


@pytest.mark.parametrize(
    ("ms", "text"),
    [(5_025_000, "1:23:45"), (65_000, "1:05"), (5_000, "0:05"), (0, "0:00")],
)
def test_format_timecode(ms: int, text: str) -> None:
    assert format_timecode(ms) == text


def test_format_timecode_always_hours() -> None:
    assert format_timecode(5_000, always_hours=True) == "0:00:05"


@pytest.mark.parametrize(
    ("ms", "spoken"),
    [
        (5_025_000, "1 hour 23 minutes 45 seconds"),
        (60_000, "1 minute"),
        (0, "0 seconds"),
        (3_600_000, "1 hour"),
        (7_320_000, "2 hours 2 minutes"),
    ],
)
def test_format_spoken(ms: int, spoken: str) -> None:
    assert format_spoken(ms) == spoken


def test_parse_format_roundtrip() -> None:
    for ms in (0, 1_000, 59_000, 60_000, 5_025_000, 40_000_000):
        assert parse_timecode(format_timecode(ms, always_hours=True)) == ms
