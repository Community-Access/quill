"""Internet Archive search ranks the best matches first (a listener's report).

Sorted by identifier, the first 40 results for "Yours Truly Johnny Dollar 1956"
were older uploads starting "0" to "O"; the series Old Time Radio Researchers
uploaded on 2026-10-01 ("YTJD1956...") never appeared. Browsing keeps its stable
identifier order, because paging depends on it.
"""

from __future__ import annotations

import urllib.parse

from quill.core.radio import internet_archive as ia

_EMPTY = '{"response": {"numFound": 0, "docs": []}}'


def _params(url: str) -> dict[str, list[str]]:
    return urllib.parse.parse_qs(urllib.parse.urlparse(url).query)


def test_search_asks_for_relevance_order(monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(ia, "_fetch", lambda url: seen.append(url) or _EMPTY)
    ia.search("Yours Truly Johnny Dollar 1956")
    assert "sort[]" not in _params(seen[0])


def test_browsing_keeps_its_stable_order() -> None:
    url = ia._search_url("collection:oldtimeradio AND mediatype:audio", rows=100, page=2)
    assert _params(url)["sort[]"] == ["identifier asc"]


def test_a_caller_can_still_ask_for_newest_first(monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(ia, "_fetch", lambda url: seen.append(url) or _EMPTY)
    ia.search("collection:librivoxaudio", sort="publicdate desc")
    assert _params(seen[0])["sort[]"] == ["publicdate desc"]
