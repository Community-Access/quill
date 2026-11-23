"""Every page_links pattern stays fast on 2 MB of hostile text.

Python's regular expressions have no time limit, and Find Streams reads pages
and scripts anyone can write. A pattern with an unbounded repeat beside another
can backtrack for minutes on the right input, holding a scan worker the whole
time. So each compiled pattern is run over 2 MB built to provoke exactly that
-- long words, unclosed quotes, a key with no value -- and must finish within a
second. (Regex time limits are an idea from Andre Louis's StreamSift,
https://github.com/OnjLouis/StreamSift; Python has none, so a test does it.)
"""

from __future__ import annotations

import re
import time

import pytest

from quill.core.radio import page_links

_SIZE = 2_000_000


def _fill(unit: str) -> str:
    return unit * (_SIZE // len(unit))


_HOSTILE = {
    "one long word": _fill("a"),
    "the key word, repeated": _fill("stream"),
    "keys with no value": _fill("streamUrl: "),
    "keys with an unclosed value": _fill("audio_src = 'https://"),
    "quotes never closed": _fill("'//radio"),
    "addresses run together": _fill("http://"),
    "window.open never closed": _fill("window.open( '"),
    "commas and spaces": _fill(", "),
    "whitespace": _fill(" \t\n"),
    "angle brackets": _fill("<"),
}

_PATTERNS = {
    name: value for name, value in vars(page_links).items() if isinstance(value, re.Pattern)
}


def test_the_patterns_are_found() -> None:
    assert "_ASSIGNED_URL_RE" in _PATTERNS
    assert len(_PATTERNS) >= 6


@pytest.mark.parametrize("name", sorted(_PATTERNS))
def test_each_pattern_is_fast_on_hostile_text(name: str) -> None:
    pattern = _PATTERNS[name]
    for kind, text in _HOSTILE.items():
        started = time.perf_counter()
        for _match in pattern.finditer(text):
            pass
        took = time.perf_counter() - started
        assert took < 1.0, f"{name} took {took:.1f} s on {kind}"


def test_the_bounded_key_still_finds_real_settings() -> None:
    text = (
        'var player = {streamUrl: "https://radio.example.org/live", hls_url :"//x.example/a.m3u8"}'
    )
    found = [m.group(2) for m in page_links._ASSIGNED_URL_RE.finditer(text)]
    assert found == ["https://radio.example.org/live", "//x.example/a.m3u8"]
