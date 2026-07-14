"""Tests for the twelve engine filters (§12)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from quill.core.verbosity.tokens import apply_filter


@pytest.mark.parametrize(
    ("name", "value", "arg", "expected"),
    [
        ("upper", "hello", None, "HELLO"),
        ("lower", "HELLO", None, "hello"),
        ("title", "hello world", None, "Hello World"),
        ("ordinal", 1, None, "1st"),
        ("ordinal", 2, None, "2nd"),
        ("ordinal", 3, None, "3rd"),
        ("ordinal", 4, None, "4th"),
        ("ordinal", 11, None, "11th"),
        ("ordinal", 21, None, "21st"),
        ("ordinal", 113, None, "113th"),
        ("pad", 7, "3", "007"),
        ("pad", 42, "2", "42"),
        ("pluralize", "match", None, "matches"),
        ("pluralize", "word", None, "words"),
        ("pluralize", "box", None, "boxes"),
        ("singular", "matches", None, "match"),
        ("singular", "words", None, "word"),
        ("singular", "stories", None, "story"),
        ("singular", "class", None, "class"),
        ("date_short", datetime(2026, 6, 21, 15, 45), None, "2026-06-21"),
        ("truncate", "hello world", "5", "he..."),
        ("truncate", "hi", "5", "hi"),
    ],
)
def test_filter_outputs(name: str, value: object, arg: str | None, expected: str) -> None:
    assert apply_filter(name, value, arg) == expected


def test_duration_human_from_seconds() -> None:
    assert apply_filter("duration_human", 3723, None) == "1 hour 2 minutes 3 seconds"


def test_duration_human_from_timedelta() -> None:
    assert apply_filter("duration_human", timedelta(minutes=2), None) == "2 minutes"


def test_duration_human_zero() -> None:
    assert apply_filter("duration_human", 0, None) == "0 seconds"


def test_date_long_has_no_leading_zero_day() -> None:
    out = apply_filter("date_long", datetime(2026, 6, 5), None)
    assert out == "Friday, June 5, 2026"


def test_time_strips_leading_zero_hour() -> None:
    assert apply_filter("time", datetime(2026, 6, 21, 15, 45), None) == "3:45 PM"


def test_unknown_filter_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        apply_filter("nope", "x", None)
