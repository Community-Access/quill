"""Icecast / SHOUTcast servers a listener adds themselves."""

from __future__ import annotations

import json

import pytest

from quill.core.radio import my_servers
from quill.core.radio.my_servers import (
    MyServersError,
    ServerStore,
    normalize_root,
    parse_icecast,
    parse_shoutcast,
)

_ICECAST_MANY = json.dumps({
    "icestats": {
        "source": [
            {
                "listenurl": "http://ice.example:8000/jazz",
                "server_name": "Jazz Mount",
                "title": "Miles Davis - So What",
                "genre": "Jazz",
                "bitrate": 128,
                "server_type": "audio/mpeg",
            },
            {"mount": "/talk", "server_name": "Talk Mount"},
        ]
    }
})

#: A one-mount server reports `source` as an OBJECT, not a list. This is the
#: single most common way a naive parser returns nothing -- and one-mount
#: servers are exactly the small broadcasters this branch exists for.
_ICECAST_ONE = json.dumps({
    "icestats": {"source": {"listenurl": "http://ice.example:8000/only", "server_name": "Only"}}
})


def test_normalize_root_accepts_what_people_actually_paste() -> None:
    # A stream URL is what they have in hand, not a server root.
    assert normalize_root("http://ice.example:8000/jazz") == "http://ice.example:8000"
    assert normalize_root("ice.example:8000") == "http://ice.example:8000"
    assert normalize_root("https://ice.example/") == "https://ice.example"
    assert normalize_root("") == ""
    assert normalize_root("not a url") == ""


def test_parse_icecast_reads_mounts_and_now_playing() -> None:
    stations = parse_icecast(_ICECAST_MANY, "http://ice.example:8000")
    assert [s.name for s in stations] == ["Jazz Mount", "Talk Mount"]
    assert stations[0].tags[0] == "Miles Davis - So What"
    assert stations[0].bitrate_kbps == 128
    assert stations[1].stream_url == "http://ice.example:8000/talk"


def test_parse_icecast_handles_a_single_mount_server() -> None:
    stations = parse_icecast(_ICECAST_ONE, "http://ice.example:8000")
    assert [s.name for s in stations] == ["Only"]


def test_parse_icecast_tolerates_junk() -> None:
    assert parse_icecast("not json", "http://x") == []
    assert parse_icecast(json.dumps({"icestats": {}}), "http://x") == []


def test_parse_shoutcast_v2_and_v1() -> None:
    v2 = (
        "<SHOUTCASTSERVER><SERVERTITLE>My Station</SERVERTITLE>"
        "<SONGTITLE>A Song</SONGTITLE></SHOUTCASTSERVER>"
    )
    stations = parse_shoutcast(v2, "http://sc.example:8000")
    assert stations[0].name == "My Station" and stations[0].tags == ("A Song",)
    v1 = "<HTML><body>12,1,30,100,5,128,Artist - Title</body></HTML>"
    stations = parse_shoutcast(v1, "http://sc.example:8000")
    assert stations and stations[0].tags == ("Artist - Title",)


def test_the_store_round_trips_and_refuses_duplicates(tmp_path) -> None:
    store = ServerStore(tmp_path)
    first = store.add("http://ice.example:8000/jazz", "Community Radio")
    assert first is not None and first.root == "http://ice.example:8000"
    store.add("ice.example:8000")  # the same server, pasted differently
    assert len(store.all()) == 1
    assert store.all()[0].display_name == "Community Radio"


def test_the_store_rejects_a_bad_address(tmp_path) -> None:
    assert ServerStore(tmp_path).add("nonsense") is None


def test_rename_and_remove(tmp_path) -> None:
    store = ServerStore(tmp_path)
    store.add("http://a.example:8000")
    store.rename("http://a.example:8000", "Renamed")
    assert store.all()[0].name == "Renamed"
    store.remove("http://a.example:8000")
    assert store.all() == []


def test_mounts_tries_each_status_path_and_stops_at_the_first(monkeypatch) -> None:
    asked: list[str] = []

    def fake_fetch(url: str) -> str:
        asked.append(url)
        if url.endswith("status-json.xsl"):
            raise MyServersError("no icecast here")
        return (
            "<SHOUTCASTSERVER><SERVERTITLE>S</SERVERTITLE>"
            "<SONGTITLE>x</SONGTITLE></SHOUTCASTSERVER>"
        )

    monkeypatch.setattr(my_servers, "_fetch", fake_fetch)
    stations = my_servers.mounts("http://sc.example:8000")
    assert [s.name for s in stations] == ["S"]
    assert asked[0].endswith("/status-json.xsl") and asked[1].endswith("/stat")


def test_a_server_that_answers_nothing_is_empty_not_an_error(monkeypatch) -> None:
    monkeypatch.setattr(
        my_servers, "_fetch", lambda url: (_ for _ in ()).throw(MyServersError("down"))
    )
    assert my_servers.mounts("http://x.example:8000") == []


def test_probe_reports_the_count_before_the_server_is_stored(monkeypatch) -> None:
    monkeypatch.setattr(my_servers, "_fetch", lambda url: _ICECAST_MANY)
    root, count = my_servers.probe("http://ice.example:8000/jazz")
    assert root == "http://ice.example:8000" and count == 2


def test_safe_mode_refuses() -> None:
    with pytest.raises(MyServersError):
        my_servers.refuse_in_safe_mode(True)
    with pytest.raises(MyServersError):
        my_servers.mounts("http://x.example", safe_mode=True)
