"""More places to find audio: feeds, Internet Archive items and open directories.

No live network: every address is read through a fake, and everything a fake
returns is treated as untrusted, as a real answer is.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.radio import audio_sources as src
from quill.core.radio import audio_sources_io as io
from quill.core.radio import find_streams_view as view
from quill.core.radio.find_streams_text import row_status, size_text
from quill.core.radio.live_check import HttpReply
from quill.core.radio.page_links import PageStreamCandidate

APACHE = """<html><head><title>Index of /music/album</title></head><body>
<h1>Index of /music/album</h1>
<table>
<tr><th><a href="?C=N;O=D">Name</a></th><th><a href="?C=M;O=A">Last modified</a></th></tr>
<tr><td><a href="/music/">Parent Directory</a></td></tr>
<tr><td><a href="Track%2010.mp3">Track 10.mp3</a></td><td align="right">2020-05-01 14:30  </td>
<td align="right">3.4M</td></tr>
<tr><td><a href="track 2.MP3">track 2.MP3</a></td><td align="right">2020-04-02 09:00  </td>
<td align="right">812K</td></tr>
<tr><td><a href="Track%201.ogg">Track 1.ogg</a></td><td align="right">2021-01-15 10:00  </td>
<td align="right">3412345</td></tr>
<tr><td><a href="cover.jpg">cover.jpg</a></td><td>2020-01-01 00:00</td><td>50K</td></tr>
<tr><td><a href="notes.txt">notes.txt</a></td><td>2020-01-01 00:00</td><td>1K</td></tr>
<tr><td><a href="extras/">extras/</a></td><td>2020-01-01 00:00</td><td>-</td></tr>
<tr><td><a href="https://evil.example/x.mp3">x.mp3</a></td><td>-</td></tr>
<tr><td><a href="javascript:alert(1).mp3">bad.mp3</a></td></tr>
</table></body></html>"""

NGINX = """<html><head><title>Index of /pod/</title></head><body><h1>Index of /pod/</h1><hr><pre>
<a href="../">../</a>
<a href="Ep%2001.m4a">Ep 01.m4a</a>                          03-Feb-2022 18:20            12345678
<a href="Ep%2002.m4a">Ep 02.m4a</a>                          10-Feb-2022 18:20            23456789
</pre><hr></body></html>"""


def test_directory_reading_keeps_audio_on_the_same_site_with_size_and_date() -> None:
    rows = src.directory_tracks(APACHE, "https://files.example.org/music/album/")
    names = [r.label for r in rows]
    assert names == ["Track 10.mp3", "track 2.MP3", "Track 1.ogg"]
    ten, two, one = rows
    assert ten.url == "https://files.example.org/music/album/Track%2010.mp3"
    assert (ten.size_bytes, ten.modified, ten.codec) == (
        int(3.4 * 1024**2),
        "2020-05-01 14:30",
        "MP3",
    )
    assert two.size_bytes == 812 * 1024 and two.modified == "2020-04-02 09:00"
    assert one.size_bytes == 3412345 and one.codec == "Ogg"
    assert all(r.check == "file" and r.label_is_name for r in rows)


def test_directory_reading_handles_the_other_common_layout() -> None:
    rows = src.directory_tracks(NGINX, "http://files.example.org/pod/")
    assert [(r.label, r.size_bytes, r.modified) for r in rows] == [
        ("Ep 01.m4a", 12345678, "2022-02-03 18:20"),
        ("Ep 02.m4a", 23456789, "2022-02-10 18:20"),
    ]
    assert rows[0].codec == "AAC"


def test_directory_detection() -> None:
    assert src.looks_like_directory(APACHE) and src.looks_like_directory(NGINX)
    assert not src.looks_like_directory("<html><body><audio src='a.mp3'></audio></body></html>")


def test_a_directory_is_capped() -> None:
    page = "<title>Index of /</title>" + "".join(
        f'<a href="t{i}.mp3">t{i}.mp3</a> 2020-01-01 00:00 1K\n' for i in range(src.MAX_TRACKS + 50)
    )
    assert len(src.directory_tracks(page, "https://x.example/")) == src.MAX_TRACKS


def test_names_sort_naturally_and_case_insensitively_so_track_2_precedes_track_10() -> None:
    rows = src.directory_tracks(APACHE, "https://files.example.org/music/album/")
    shown = view.visible(rows, view.ViewState(order=view.NAME))
    assert [rows[i].label for i in shown] == ["Track 1.ogg", "track 2.MP3", "Track 10.mp3"]
    assert view.natural_key("Track 2") < view.natural_key("track 10")
    assert view.natural_key("TRACK 02") == view.natural_key("track 2")
    assert view.natural_key("Écoute 3") < view.natural_key("ecoute 12")


def test_size_date_and_format_orders_and_only_when_the_rows_have_them() -> None:
    rows = src.directory_tracks(APACHE, "https://files.example.org/music/album/")
    by = lambda order: [rows[i].label for i in view.visible(rows, view.ViewState(order=order))]  # noqa: E731
    assert by(view.SIZE) == ["Track 10.mp3", "Track 1.ogg", "track 2.MP3"]
    assert by(view.DATE) == ["Track 1.ogg", "Track 10.mp3", "track 2.MP3"]
    assert by(view.FORMAT)[0] in {"Track 10.mp3", "track 2.MP3"}  # MP3 before Ogg
    assert [view.offered(o, rows) for o in (view.SIZE, view.DATE, view.FORMAT)] == [True] * 3
    streams = [PageStreamCandidate(url="http://s/1", reason="x", check="live")]
    assert [view.offered(o, streams) for o in (view.SIZE, view.DATE, view.FORMAT)] == [False] * 3
    assert view.visible(streams, view.ViewState(order=view.SIZE)) == [0]  # falls back to scan order


def test_a_row_says_its_metadata_as_you_move_to_it() -> None:
    rows = src.directory_tracks(APACHE, "https://files.example.org/music/album/")
    assert row_status(rows[0]) == (
        "Audio file, not a live stream: Track 10.mp3, MP3, 3.4 MB, 2020-05-01 14:30"
    )
    assert size_text(0) == "" and size_text(900) == "1 KB" and size_text(5 * 1024**3) == "5.0 GB"


def test_archive_identifier() -> None:
    assert src.archive_identifier("https://archive.org/details/OTRR_Gunsmoke") == "OTRR_Gunsmoke"
    assert src.archive_identifier("archive.org/details/abc/extra") == "abc"
    assert src.archive_identifier("https://www.archive.org/details/a.b-c_1") == "a.b-c_1"
    for bad in (
        "https://archive.org/",
        "https://archive.org/search?query=x",
        "https://evil.example/details/abc",
        "https://archive.org.evil.example/details/abc",
        "https://archive.org/details/../x",
        "https://archive.org/details/a b",
        "",
    ):
        assert src.archive_identifier(bad) == ""


FEED = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>The Show</title>
<link>https://show.example/</link>
<item><title>Ep 2</title><guid>2</guid><pubDate>Tue, 05 Mar 2024 10:00:00 GMT</pubDate>
<enclosure url="https://cdn.example/2.mp3" length="123" type="audio/mpeg"/></item>
<item><title>Ep 1</title><guid>1</guid><pubDate>Tue, 27 Feb 2024 10:00:00 GMT</pubDate>
<enclosure url="https://cdn.example/redirect?id=1" length="123" type="audio/mpeg"/></item>
<item><title>No audio</title><guid>0</guid></item>
<item><title>Video</title><guid>v</guid>
<enclosure url="ftp://cdn.example/v.mp3" length="1" type="audio/mpeg"/></item>
</channel></rss>"""


def _reply(body: bytes | str, content_type: str = "text/html", url: str = "") -> HttpReply:
    data = body.encode() if isinstance(body, str) else body
    return HttpReply(200, {"Content-Type": content_type}, data, url)


def _fetch(pages: dict[str, HttpReply]) -> Any:
    seen: list[str] = []

    def fetch(url: str, max_bytes: int) -> HttpReply:
        seen.append(url)
        for part, reply in pages.items():
            if url.endswith(part):
                return reply
        return HttpReply(404, {}, b"")

    fetch.seen = seen  # type: ignore[attr-defined]
    return fetch


def test_a_podcast_feed_lists_each_episodes_audio() -> None:
    fetch = _fetch({"/feed.xml": _reply(FEED, "application/rss+xml")})
    found = io.find_audio("https://show.example/feed.xml", safe_mode=False, fetch=fetch)
    assert found is not None and found.scan.page_title == "The Show"
    rows = found.scan.candidates
    assert [r.label for r in rows] == ["Ep 2", "Ep 1"]
    assert rows[0].url == "https://cdn.example/2.mp3" and rows[0].modified == "2024-03-05"
    assert rows[1].codec == ""  # a redirect link: audio, format unknown
    assert all(r.check == "file" for r in rows) and found.how.startswith("Read as a podcast feed")


def test_a_directory_is_read_after_robots_and_a_home_page_is_not_read_twice() -> None:
    fetch = _fetch({
        "/robots.txt": _reply("User-agent: *\nDisallow: /private/\n"),
        "/album/": _reply(APACHE),
    })
    found = io.find_audio("https://files.example.org/music/album/", safe_mode=False, fetch=fetch)
    assert found is not None and len(found.scan.candidates) == 3
    assert found.how == "Read as an open directory of audio files."
    home = _fetch({})
    assert io.find_audio("https://www.kexp.org/", safe_mode=False, fetch=home) is None
    assert io.find_audio("https://www.kexp.org/listen-live", safe_mode=False, fetch=home) is None
    assert home.seen == []  # a station's page is left to the usual scan


def test_robots_txt_is_respected_with_one_plain_sentence() -> None:
    fetch = _fetch({
        "/robots.txt": _reply("User-agent: *\nDisallow: /music/\n", "text/plain"),
        "/album/": _reply(APACHE),
    })
    found = io.find_audio("https://files.example.org/music/album/", safe_mode=False, fetch=fetch)
    assert found is not None and found.scan.candidates == [] and found.how == io.REFUSED_BY_ROBOTS
    assert not any(url.endswith("/album/") for url in fetch.seen)  # the page itself was never read


def test_a_missing_or_unreadable_robots_txt_forbids_nothing() -> None:
    assert io.robots_allow("https://x.example/a/", lambda u, n: HttpReply(404, {}, b"")) is True

    def boom(url: str, max_bytes: int) -> HttpReply:
        raise OSError("down")

    assert io.robots_allow("https://x.example/a/", boom) is True


def test_a_page_that_is_neither_gets_the_usual_scan() -> None:
    fetch = _fetch({"/podcast/": _reply("<html><body><audio src='a.mp3'></audio></body></html>")})
    assert io.find_audio("https://x.example/podcast/", safe_mode=False, fetch=fetch) is None


def test_an_internet_archive_item_lists_its_audio_files() -> None:
    files = [
        SimpleNamespace(name="Show 2", stream_url="https://archive.org/download/id/Show%202.mp3"),
        SimpleNamespace(name="Show 10", stream_url="https://archive.org/download/id/Show%2010.mp3"),
        SimpleNamespace(name="Cover", stream_url="https://archive.org/download/id/cover.jpg"),
    ]
    found = io.find_audio(
        "https://archive.org/details/id", safe_mode=False, archive_files=lambda item: files
    )
    assert found is not None and [r.label for r in found.scan.candidates] == ["Show 2", "Show 10"]
    assert found.how == "Read as an Internet Archive item."


def test_an_archive_item_that_cannot_be_read_says_so_plainly() -> None:
    def down(item: str) -> list[object]:
        raise OSError("x")

    found = io.find_audio("archive.org/details/id", safe_mode=False, archive_files=down)
    assert found is not None and found.how == "The Internet Archive did not answer for that item."
    assert (
        io.find_audio("archive.org/details/id", safe_mode=True) is None
    )  # Safe Mode reads nothing


@pytest.mark.parametrize("bad", ["magnet:?xt=urn:btih:x", "https://x.example/a.torrent"])
def test_torrents_and_web_seeds_are_not_audio(bad: str) -> None:
    assert src.track(bad, "x", reason="r") is None
