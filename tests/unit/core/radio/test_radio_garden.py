"""Radio Garden: pasted station pages, searching, and resolving to the real stream.

No live network: Radio Garden has no official API and sits behind a bot filter,
so every answer here is a fake, including the page it answers with when it
refuses a program.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from quill.core.radio import find_fallback_io as io
from quill.core.radio import radio_garden as rg
from quill.core.radio.live_check import HttpReply

MP3 = (Path(__file__).parent / "fixtures" / "live_check" / "mp3_prefix.bin").read_bytes()
CHALLENGE = b"<!DOCTYPE html><title>Attention Required! | Cloudflare</title>"


def _search_payload(*rows: tuple[str, str, str]) -> bytes:
    hits = [
        {"_source": {"type": kind, "title": title, "url": url, "subtitle": "Seattle, USA"}}
        for kind, title, url in rows
    ]
    return json.dumps({"hits": {"hits": hits}}).encode()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://radio.garden/listen/kexp-90-3/Zk1UxX-Y", "Zk1UxX-Y"),
        ("radio.garden/listen/kexp/Zk1UxX-Y/", "Zk1UxX-Y"),
        ("http://www.radio.garden/listen/a/Pj3gGpMY", "Pj3gGpMY"),
        ("https://radio.garden/visit/seattle/abc123", ""),  # a place, not a station
        ("https://radio.garden/", ""),
        ("https://evil.example/radio.garden/listen/x/Zk1UxX-Y", ""),
        ("https://radio.garden.evil.example/listen/x/Zk1UxX-Y", ""),
        ("kexp", ""),
        ("", ""),
    ],
)
def test_station_id(text: str, expected: str) -> None:
    assert rg.station_id(text) == expected


def test_parse_search_keeps_only_stations_and_drops_junk() -> None:
    payload = json.loads(
        _search_payload(
            ("channel", "KEXP 90.3", "/listen/kexp-90-3/Zk1UxX-Y"),
            ("place", "Seattle", "/visit/seattle/abc123"),
            ("channel", "KEXP 90.3", "/listen/kexp-90-3/Zk1UxX-Y"),  # a repeat
            ("channel", "  ", "/listen/blank/QWERTY12"),
            ("channel", "No Link", "/not-a-station"),
            ("channel", "Evil", "/listen/x/../../etc"),
        )
    )
    assert rg.parse_search(payload) == [rg.Hit("Zk1UxX-Y", "KEXP 90.3", "Seattle, USA")]
    for junk in (None, 5, [], {}, {"hits": 3}, {"hits": {"hits": "x"}}, {"hits": {"hits": [5]}}):
        assert rg.parse_search(junk) == []


def _fetch(routes: dict[str, Any]) -> rg.Fetch:
    def fetch(url: str, timeout: float, max_bytes: int) -> HttpReply:
        for part, answer in routes.items():
            if part in url:
                if isinstance(answer, BaseException):
                    raise answer
                return answer
        raise OSError("unexpected " + url)

    return fetch


def test_search_returns_hits_and_none_when_the_service_does_not_answer() -> None:
    ok = HttpReply(200, {}, _search_payload(("channel", "KEXP", "/listen/kexp/Zk1UxX-Y")))
    assert [h.id for h in rg.search("kexp", _fetch({"/api/search": ok})) or []] == ["Zk1UxX-Y"]
    challenge = HttpReply(403, {"Content-Type": "text/html"}, CHALLENGE)
    assert rg.search("kexp", _fetch({"/api/search": challenge})) is None
    page = HttpReply(200, {"Content-Type": "text/html"}, CHALLENGE)  # 200 but not JSON
    assert rg.search("kexp", _fetch({"/api/search": page})) is None
    assert rg.search("kexp", _fetch({"/api/search": OSError("down")})) is None
    assert rg.search("   ", _fetch({})) == []  # nothing typed: nothing asked


def test_the_query_is_encoded_into_the_address() -> None:
    seen: list[str] = []

    def fetch(url: str, timeout: float, max_bytes: int) -> HttpReply:
        seen.append(url)
        return HttpReply(200, {}, b"{}")

    rg.search("a b&c=d", fetch)
    assert seen == ["https://radio.garden/api/search?q=a%20b%26c%3Dd"]


def test_resolve_follows_the_redirect_to_the_real_stream() -> None:
    real = "https://stream.example.org/kexp.mp3"
    reply = HttpReply(200, {"Content-Type": "audio/mpeg", "icy-name": "KEXP 90.3"}, MP3, real)
    candidate = rg.resolve(rg.Hit("Zk1UxX-Y", "KEXP"), _fetch({"/listen/Zk1UxX-Y": reply}))
    assert candidate is not None
    assert candidate.url == real and "radio.garden" not in candidate.url
    assert candidate.label == "KEXP" and candidate.label_is_name
    assert candidate.reason == "found in the Radio Garden directory"
    assert candidate.check in ("live", "file")


def test_resolve_refuses_what_is_not_a_stream() -> None:
    gone = HttpReply(404, {}, b"", "https://stream.example.org/x")
    stays = HttpReply(200, {"Content-Type": "audio/mpeg"}, MP3, "")  # never left Radio Garden
    page = HttpReply(200, {"Content-Type": "text/html"}, CHALLENGE, "https://other.example/x")
    for reply in (gone, stays, page):
        assert rg.resolve(rg.Hit("Zk1UxX-Y", "KEXP"), _fetch({"/listen/": reply})) is None
    assert rg.resolve(rg.Hit("Zk1UxX-Y", "KEXP"), _fetch({"/listen/": OSError("x")})) is None


def test_channel_title_reads_the_station_name() -> None:
    body = json.dumps({"data": {"title": " KEXP  90.3 "}}).encode()
    assert rg.channel_title("Zk1UxX-Y", _fetch({"/channel/": HttpReply(200, {}, body)})) == (
        "KEXP 90.3"
    )
    assert rg.channel_title("Zk1UxX-Y", _fetch({"/channel/": HttpReply(403, {}, CHALLENGE)})) == ""


# -- Find Streams ------------------------------------------------------------------


def _garden_routes(real: str = "https://stream.example.org/kexp.mp3") -> dict[str, Any]:
    return {
        "/api/search": HttpReply(
            200, {}, _search_payload(("channel", "KEXP", "/listen/kexp/Zk1UxX-Y"))
        ),
        "/content/channel/": HttpReply(
            200, {}, json.dumps({"data": {"title": "KEXP 90.3"}}).encode()
        ),
        "/content/listen/": HttpReply(200, {"Content-Type": "audio/mpeg"}, MP3, real),
    }


def test_a_pasted_station_page_gives_its_real_stream_and_says_where_from() -> None:
    found = io._garden_page(
        "Zk1UxX-Y", "https://radio.garden/listen/kexp/Zk1UxX-Y", False, _fetch(_garden_routes())
    )
    assert [c.url for c in found.scan.candidates] == ["https://stream.example.org/kexp.mp3"]
    assert found.scan.page_title == "KEXP 90.3" and found.how == "Found by Radio Garden."


def test_a_pasted_page_with_no_playback_says_so_plainly() -> None:
    routes = _garden_routes()
    routes["/content/listen/"] = HttpReply(404, {}, b"", "https://radio.garden/x")
    found = io._garden_page(
        "Zk1UxX-Y", "https://radio.garden/listen/kexp/Zk1UxX-Y", False, _fetch(routes)
    )
    assert found.scan.candidates == [] and found.how == rg.NO_PLAYBACK


def test_a_pasted_page_when_radio_garden_refuses_the_program() -> None:
    challenge = HttpReply(403, {"Content-Type": "text/html"}, CHALLENGE)
    found = io._garden_page(
        "Zk1UxX-Y",
        "https://radio.garden/listen/kexp/Zk1UxX-Y",
        False,
        _fetch({"/content/": challenge}),
    )
    assert found.scan.candidates == [] and found.how == rg.NOT_ANSWERING
    assert "403" not in found.how and "Cloudflare" not in found.how


def test_safe_mode_contacts_radio_garden_not_at_all() -> None:
    def boom(url: str, timeout: float, max_bytes: int) -> HttpReply:
        raise AssertionError("contacted in Safe Mode")

    found = io._garden_page("Zk1UxX-Y", "https://radio.garden/listen/k/Zk1UxX-Y", True, boom)
    assert found.scan.candidates == [] and "Safe Mode" in found.how
    assert io.search_directories("kexp", safe_mode=True, garden=boom) == []


def test_a_name_search_adds_radio_garden_stations_and_caps_the_lookups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(io.radio_browser, "search_stations", lambda *a, **k: [])
    monkeypatch.setattr(io.iprd, "search_stations", lambda *a, **k: [])
    monkeypatch.setattr(io.iprd, "catalog", lambda **k: [])
    rows = [("channel", f"KEXP {i}", f"/listen/kexp-{i}/Id{i:06d}") for i in range(12)]
    asked: list[str] = []

    def fetch(url: str, timeout: float, max_bytes: int) -> HttpReply:
        if "/api/search" in url:
            return HttpReply(200, {}, _search_payload(*rows))
        asked.append(url)
        return HttpReply(
            200, {"Content-Type": "audio/mpeg"}, MP3, f"https://s.example/{len(asked)}"
        )

    found = io.search_directories("kexp", garden=fetch)
    assert len(found) == rg.MAX_PLAYBACK_LOOKUPS == len(asked)
    assert all(c.reason == "found in the Radio Garden directory" for c in found)


def test_a_name_search_notes_when_radio_garden_did_not_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(io.radio_browser, "search_stations", lambda *a, **k: [])
    monkeypatch.setattr(io.iprd, "search_stations", lambda *a, **k: [])
    monkeypatch.setattr(io.iprd, "catalog", lambda **k: [])
    notes: list[str] = []
    refused = _fetch({"/api/search": HttpReply(403, {"Content-Type": "text/html"}, CHALLENGE)})
    assert io.search_directories("kexp", garden=refused, notes=notes) == []
    assert notes == [rg.NOT_ANSWERING]
