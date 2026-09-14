"""Recognising a website address, and normalising one.

Both predicates moved out of :mod:`quill.core.radio.link_finder` and the Find
Stations dialog when a second search box needed to ask the same question
(#1491): pasting ``oj991.com`` into Search All Sources went to every directory
as a *name*, Radio Browser matched the token "com", and the answer was 33 rows
of Cruisin92.com and STAR1079.com without the station anywhere in it.
"""

from __future__ import annotations

import pytest

from quill.core.radio.page_url import looks_like_url, normalize_page_url


@pytest.mark.parametrize(
    "text",
    [
        "https://example.com/stream",
        "http://example.com",
        "example.com/radio",
        "wnyc.org",
        "oj991.com",
        "www.oj991.com",
    ],
)
def test_addresses_are_recognised(text: str) -> None:
    assert looks_like_url(text) is True


@pytest.mark.parametrize(
    "text",
    ["Jazz FM", "news", "", "   ", "BBC Radio 1", "oj991.com and more", "trailing."],
)
def test_name_queries_are_not_addresses(text: str) -> None:
    """A station name is the common case, and must never be treated as a site."""
    assert looks_like_url(text) is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("oj991.com", "https://oj991.com"),
        ("  oj991.com  ", "https://oj991.com"),
        ("http://oj991.com/", "https://oj991.com/"),
        ("https://oj991.com/live", "https://oj991.com/live"),
        ("", ""),
    ],
)
def test_normalising_prefers_https(raw: str, expected: str) -> None:
    assert normalize_page_url(raw) == expected


def test_the_dialog_still_exposes_the_predicate_under_its_old_name() -> None:
    """Callers that learned it from the Find Stations dialog keep working."""
    from quill.ui.radio.station_browser_dialog import looks_like_url as from_dialog

    assert from_dialog is looks_like_url
