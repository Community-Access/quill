"""Publisher times are validated before anything plays them (earshot.md E2). Pure."""

from __future__ import annotations

import json

import pytest

from quill.core.podcasts.chapters import parse_chapters
from quill.core.podcasts.namespace_tags import _seconds_to_ms as feed_seconds_to_ms
from quill.core.podcasts.time_values import ms_or_none, seconds_to_ms_or_none
from quill.core.podcasts.transcripts import _seconds_to_ms as cue_seconds_to_ms


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (12.5, 12_500),
        (0, 0),
        (float("nan"), None),
        (float("inf"), None),
        (-5, None),
        (True, None),
        (1e300, None),
        ("12.5", None),  # text only where the format is text
        (None, None),
    ],
)
def test_seconds_to_ms_or_none(value: object, expected: int | None) -> None:
    assert seconds_to_ms_or_none(value) == expected


def test_text_is_accepted_where_asked() -> None:
    assert seconds_to_ms_or_none(" 12.5 ", allow_text=True) == 12_500
    assert seconds_to_ms_or_none("inf", allow_text=True) is None
    assert seconds_to_ms_or_none("abc", allow_text=True) is None


def test_ms_or_none() -> None:
    assert ms_or_none(1500) == 1500
    assert ms_or_none(float("nan")) is None
    assert ms_or_none(-1) is None


def _chapters(*starts: str) -> bytes:
    rows = ", ".join(f'{{"startTime": {start}, "title": "c{i}"}}' for i, start in enumerate(starts))
    return f'{{"version": "1.2.0", "chapters": [{rows}]}}'.encode()


def test_one_impossible_chapter_drops_only_itself() -> None:
    chapters = parse_chapters(_chapters("NaN", "10", "Infinity", "true", "1e300", "-5", "20"))
    assert [c.start_ms for c in chapters] == [10_000, 20_000]


def test_feed_and_transcript_times_never_raise() -> None:
    assert feed_seconds_to_ms("inf") == 0
    assert feed_seconds_to_ms("30") == 30_000
    assert cue_seconds_to_ms(float("inf")) == 0
    assert cue_seconds_to_ms(-3) == 0
    assert cue_seconds_to_ms("4") == 4_000


def test_json_reader_really_does_produce_these_values() -> None:
    # The premise of the module: Python's json accepts NaN and Infinity.
    data = json.loads('{"a": NaN, "b": Infinity}')
    assert data["b"] == float("inf")
