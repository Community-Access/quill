"""Find Streams remembers sites that worked, and reads more of them.

Recent websites (what is never stored, the history round trip), numbered
mirrors counted as one, listen links in other languages, and a listen
subdomain of the site's own host followed while a sibling domain is not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.radio import link_finder
from quill.core.radio import recent_websites as rw
from quill.core.radio.address_kind import is_listen_subdomain
from quill.core.radio.history import RadioHistory, load_history, save_history
from quill.core.radio.page_links import (
    PageStreamCandidate,
    StreamLinkParser,
    looks_like_listen_link,
)
from quill.core.radio.stream_mirrors import collapse_mirrors, mirror_key

# -- recent websites -----------------------------------------------------------------


@pytest.mark.parametrize(
    "address",
    [
        "https://station.example/listen?token=abc",
        "https://station.example/#player",
        "https://user:pw@station.example/",
        "ftp://station.example/",
        "http://192.168.1.1/",
        "http://nas.local/",
        "",
        "https://station.example/a b",
    ],
)
def test_addresses_that_are_never_remembered(address: str) -> None:
    assert not rw.storable(address)
    assert rw.remember((), address) == ()


def test_newest_first_no_copies_and_at_most_ten() -> None:
    recent: tuple[str, ...] = ()
    for n in range(12):
        recent = rw.remember(recent, f"https://s{n}.example/")
    assert len(recent) == rw.MAX_RECENT_WEBSITES
    assert recent[0] == "https://s11.example/"
    recent = rw.remember(recent, "https://S5.example")
    assert recent[0] == "https://S5.example"
    assert sum(1 for r in recent if "s5." in r.lower()) == 1


def test_the_history_round_trip(tmp_path: Path) -> None:
    history = RadioHistory()
    history.recent_websites = ("https://kxyz.example/", "https://wabc.example/live")
    save_history(tmp_path, history)
    assert load_history(tmp_path).recent_websites == history.recent_websites


def test_a_stored_address_that_should_not_be_there_is_dropped() -> None:
    raw = ["https://ok.example/", "https://bad.example/?session=1", 5, "https://ok.example"]
    assert rw.from_json(raw) == ("https://ok.example/",)


# -- numbered mirrors ----------------------------------------------------------------


def _c(url: str, check: str = "live") -> PageStreamCandidate:
    return PageStreamCandidate(url=url, reason="audio tag", check=check)


def test_numbered_mirrors_are_one_stream_and_the_best_is_kept() -> None:
    rows = [
        _c("http://ice1.example.org/live", "not checked"),
        _c("http://ice2.example.org/live"),
        _c("https://ice3.example.org/live"),
        _c("http://ice4.example.org/live"),
        _c("http://ice1.example.org/other"),  # another path: another stream
        _c("http://ice1.example.org:8000/live"),  # another port
        _c("http://ice.example.org/live"),  # no number: not a mirror
    ]
    kept = [c.url for c in collapse_mirrors(rows)]
    assert kept == [
        "https://ice3.example.org/live",
        "http://ice1.example.org/other",
        "http://ice1.example.org:8000/live",
        "http://ice.example.org/live",
    ]


def test_only_the_number_may_differ() -> None:
    assert mirror_key("http://jazz1.example.org/live") != mirror_key(
        "http://rock1.example.org/live"
    )
    assert mirror_key("http://ice.example.org/live") == ""
    assert mirror_key("https://18373.live.streamtheworld.com/KKSEFM") == mirror_key(
        "https://16613.live.streamtheworld.com/KKSEFM"
    )


def test_the_scan_collapses_mirrors(monkeypatch: pytest.MonkeyPatch) -> None:
    page = (
        '<audio src="https://ice1.radio.example/live.mp3"></audio>'
        '<audio src="https://ice2.radio.example/live.mp3"></audio>'
        '<audio src="https://ice3.radio.example/live.mp3"></audio>'
    )
    monkeypatch.setattr(link_finder, "_fetch_html", lambda url: page)
    result = link_finder.scan_page_for_streams("https://station.example/")
    assert [c.url for c in result.candidates] == ["https://ice1.radio.example/live.mp3"]


# -- listen links in other languages --------------------------------------------------


@pytest.mark.parametrize(
    ("href", "label"),
    [
        ("/en-direct/", ""),  # French path
        ("/radio/ao-vivo", ""),  # Portuguese path
        ("/direkt", ""),  # German path
        ("/ways-to-listen/", ""),
        ("/player.php", "Écouter en direct"),
        ("/x", "Ouvir ao vivo"),
        ("/x", "Live hören"),
        ("/x", "Lyssna live"),
        ("/x", "Ascolta in diretta"),
        ("/x", "Luister live"),
        ("/x", "Escuchar en vivo"),
    ],
)
def test_listen_links_in_other_languages(href: str, label: str) -> None:
    assert looks_like_listen_link(href.lower(), label)


def test_a_listen_word_must_be_a_whole_segment() -> None:
    assert not looks_like_listen_link("/ventes-en-directory/", "Nos ventes")
    assert not looks_like_listen_link("/direktor/", "")


@pytest.mark.parametrize(
    ("page", "lang"),
    [
        ('<a href="/ecouter-en-direct">Écouter en direct</a>', "fr"),
        ('<a href="/ao-vivo">Ouça</a>', "pt"),
        ('<a href="/programm">Jetzt hören</a>', "de"),
    ],
)
def test_pages_in_other_languages_are_followed(
    monkeypatch: pytest.MonkeyPatch, page: str, lang: str
) -> None:
    fetched: list[str] = []

    def fetch(url: str) -> str:
        fetched.append(url)
        if url.rstrip("/") == "https://station.example":
            return f"<html lang={lang}><body>{page}</body></html>"
        return '<audio src="https://stream.example.net/live.mp3"></audio>'

    monkeypatch.setattr(link_finder, "_fetch_html", fetch)
    result = link_finder.scan_page_for_streams("https://station.example/")
    assert [c.url for c in result.candidates] == ["https://stream.example.net/live.mp3"]
    assert len(fetched) == 2


# -- listen subdomains -------------------------------------------------------------------


def test_a_listen_subdomain_of_the_site_itself() -> None:
    page = "https://www.station.example/"
    assert is_listen_subdomain("https://listen.station.example/", page)
    assert is_listen_subdomain("https://player.station.example/live", page)
    assert not is_listen_subdomain("https://listen.station-fm.example/", page)  # sibling
    assert not is_listen_subdomain("https://listen.other.example/", page)
    assert not is_listen_subdomain("https://news.station.example/", page)


def test_a_listen_subdomain_is_followed_and_a_sibling_is_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetched: list[str] = []
    pages: dict[str, str] = {
        "https://www.station.example/": (
            '<a href="https://listen.station.example/">Player</a>'
            '<a href="https://listen.station-fm.example/">Our sister station</a>'
            '<audio src="https://cdn.example.net/jingle.mp3"></audio>'
        ),
        "https://listen.station.example/": (
            '<audio src="https://ice1.station.example/live.aac"></audio>'
        ),
    }

    def fetch(url: str) -> str:
        fetched.append(url)
        return pages.get(url, "")

    monkeypatch.setattr(link_finder, "_fetch_html", fetch)
    parser = StreamLinkParser("https://www.station.example/")
    parser.feed(pages["https://www.station.example/"])
    assert parser.portal_urls == ["https://listen.station.example/"]
    result = link_finder.scan_page_for_streams("https://www.station.example/")
    urls = [c.url for c in result.candidates]
    assert "https://ice1.station.example/live.aac" in urls
    assert "https://listen.station-fm.example/" not in fetched
