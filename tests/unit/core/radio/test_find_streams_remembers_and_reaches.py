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


def _c(
    url: str, check: str = "live", name: str = "WXYZ", codec: str = "MP3"
) -> PageStreamCandidate:
    return PageStreamCandidate(
        url=url, reason="audio tag", check=check, stream_name=name, codec=codec
    )


def test_live_numbered_mirrors_of_one_stream_are_one_row_https_first() -> None:
    rows = [
        _c("http://ice2.example.org/live"),
        _c("https://ice3.example.org/live", name="wxyz"),  # the name casefolded
        _c("http://ice4.example.org/live"),
        _c("http://ice1.example.org/other"),  # another path: another stream
        _c("http://ice1.example.org:8000/live"),  # another port
        _c("http://ice.example.org/live"),  # no number: not a mirror
    ]
    collapsed = collapse_mirrors(rows)
    assert [c.url for c in collapsed.rows] == [
        "https://ice3.example.org/live",
        "http://ice1.example.org/other",
        "http://ice1.example.org:8000/live",
        "http://ice.example.org/live",
    ]
    assert (collapsed.copies, collapsed.groups) == (3, 1)


def test_rows_not_heard_to_be_the_same_stream_are_never_merged() -> None:
    rows = [
        _c("http://ice1.example.org/live", "not checked"),
        _c("http://ice2.example.org/live", "not checked"),
        _c("http://ice3.example.org/live", name="Other FM"),  # another name
        _c("http://ice4.example.org/live", codec="AAC"),  # another codec
        _c("http://ice5.example.org/live"),
    ]
    collapsed = collapse_mirrors(rows)
    assert len(collapsed.rows) == 5
    assert (collapsed.copies, collapsed.groups) == (0, 0)


def test_the_mirror_note_is_in_the_status_line_only() -> None:
    from quill.core.radio.find_streams_text import status_label, summary_sentence
    from quill.core.radio.stream_mirrors import mirrors_sentence

    rows = [_c("https://ice1.example.org/live")]
    counts = {"checked": True, "mirror_copies": 3, "mirror_groups": 1}
    assert status_label(rows, **counts).endswith(
        "Showed 3 numbered copies of the same stream as one."
    )
    assert "numbered" not in summary_sentence(rows, **counts)
    assert mirrors_sentence(5, 2) == "Showed 5 numbered copies of 2 streams as one row each."


def test_only_the_number_may_differ() -> None:
    assert mirror_key("http://jazz1.example.org/live") != mirror_key(
        "http://rock1.example.org/live"
    )
    assert mirror_key("http://ice.example.org/live") == ""
    assert mirror_key("https://18373.live.streamtheworld.com/KKSEFM") == mirror_key(
        "https://16613.live.streamtheworld.com/KKSEFM"
    )


def test_the_scan_collapses_live_mirrors(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.radio import live_check

    page = (
        '<audio src="https://ice1.radio.example/live.mp3"></audio>'
        '<audio src="https://ice2.radio.example/live.mp3"></audio>'
        '<audio src="https://ice3.radio.example/live.mp3"></audio>'
    )
    monkeypatch.setattr(link_finder, "_fetch_html", lambda url: page)
    monkeypatch.setattr(
        link_finder.live_check,
        "check_urls",
        lambda urls, get, **k: {
            u: live_check.Verdict(live_check.LIVE, codec="MP3", name="WXYZ") for u in urls
        },
    )
    result = link_finder.scan_page_for_streams("https://station.example/", check_live=True)
    assert [c.url for c in result.candidates] == ["https://ice1.radio.example/live.mp3"]
    assert (result.mirror_copies, result.mirror_groups) == (3, 1)


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
